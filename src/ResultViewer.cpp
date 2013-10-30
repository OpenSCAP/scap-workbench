/*
 * Copyright 2013 Red Hat Inc., Durham, North Carolina.
 * All Rights Reserved.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 *
 * Authors:
 *      Martin Preisler <mpreisle@redhat.com>
 */

#include "ResultViewer.h"
#include "Scanner.h"
#include <QFileDialog>
#include <QDesktopServices>
#include <QMessageBox>
#ifdef SCAP_WORKBENCH_USE_WEBKIT
#   include <QWebFrame>
#endif

ResultViewer::ResultViewer(QWidget* parent):
    QDialog(parent)
{
    mUI.setupUi(this);

    QObject::connect(
        mUI.saveResultsButton, SIGNAL(released()),
        this, SLOT(saveResults())
    );

    QObject::connect(
        mUI.saveReportButton, SIGNAL(released()),
        this, SLOT(saveReport())
    );

    QObject::connect(
        mUI.openReportButton, SIGNAL(released()),
        this, SLOT(openReport())
    );

    QObject::connect(
        mUI.saveARFButton, SIGNAL(released()),
        this, SLOT(saveARF())
    );

    QObject::connect(
        mUI.closeButton, SIGNAL(released()),
        this, SLOT(reject())
    );

    mUI.webViewContainer->setLayout(new QVBoxLayout());

#ifdef SCAP_WORKBENCH_USE_WEBKIT
    mWebView = new QWebView(mUI.webViewContainer);
    mWebView->page()->setLinkDelegationPolicy(QWebPage::DelegateAllLinks);

    QObject::connect(
        mWebView, SIGNAL(linkClicked(const QUrl&)),
        this, SLOT(webViewLinkClicked(const QUrl&))
    );

    mUI.webViewContainer->layout()->addWidget(mWebView);
#else
    mNoWebKitNotification = new QLabel(mUI.webViewContainer);
    mNoWebKitNotification->setText(
        "Workbench was compiled without WebKit support.\n"
        "Report can't be viewed directly in the application.\n"
        "Please click \"Open report\" to view it in an external "
        "application instead.");
    mNoWebKitNotification->setWordWrap(true);
    mNoWebKitNotification->setAlignment(Qt::AlignCenter);
    mUI.webViewContainer->layout()->addWidget(mNoWebKitNotification);
#endif
}

ResultViewer::~ResultViewer()
{}

void ResultViewer::clear()
{
#ifdef SCAP_WORKBENCH_USE_WEBKIT
    mWebView->setContent(QByteArray());
#endif
}

void ResultViewer::loadContent(Scanner *scanner)
{
    mReport.clear();
    scanner->getReport(mReport);

#ifdef SCAP_WORKBENCH_USE_WEBKIT
    mWebView->setContent(mReport);
#endif

    mResults.clear();
    scanner->getResults(mResults);

    mARF.clear();
    scanner->getARF(mARF);
}

const QByteArray& ResultViewer::getARF() const
{
    return mARF;
}

void ResultViewer::saveReport()
{
    const QString filename = QFileDialog::getSaveFileName(this, "Save Report (HTML)", QString(), "HTML Report (*.html)");

    if (filename == QString::Null())
        return;

    QFile file(filename);
    file.open(QIODevice::WriteOnly);
    file.write(mReport);
    file.close();
}

void ResultViewer::openReport()
{
    mReportFile.open();
    mReportFile.write(mReport);
    mReportFile.flush();

    QDesktopServices::openUrl(QUrl::fromLocalFile(mReportFile.fileName()));

    mReportFile.close();

    // the temporary file will be destroyed when scap-workbench closes
}

void ResultViewer::saveResults()
{
    const QString filename = QFileDialog::getSaveFileName(this, "Save as XCCDF Results", QString(), "XCCDF Results (*.xml)");

    if (filename == QString::Null())
        return;

    QFile file(filename);
    file.open(QIODevice::WriteOnly);
    file.write(mResults);
    file.close();
}

void ResultViewer::saveARF()
{
    const QString filename = QFileDialog::getSaveFileName(this, "Save as Result DataStream / ARF", QString(), "Result DataStream / ARF (*.xml)");

    if (filename == QString::Null())
        return;

    QFile file(filename);
    file.open(QIODevice::WriteOnly);
    file.write(mARF);
    file.close();
}


void ResultViewer::webViewLinkClicked(const QUrl& url)
{
#ifdef SCAP_WORKBENCH_USE_WEBKIT
    if (!url.isRelative())
        QMessageBox::information(this, "External URL handling", "Sorry, but external URLs can't be followed from within scap-workbench.");
    else if (!url.path().isEmpty())
        QMessageBox::information(this, "Relative URL handling", "Sorry, but this web viewer will not follow any pages other than what's already loaded (only fragment URLs are allowed).");

    const QString fragment = url.fragment();

    mWebView->page()->currentFrame()->scrollToAnchor(fragment);
#endif
}
