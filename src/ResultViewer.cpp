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
#include "Evaluator.h"
#include <QFileDialog>

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
        mUI.saveARFButton, SIGNAL(released()),
        this, SLOT(saveARF())
    );

    QObject::connect(
        mUI.closeButton, SIGNAL(released()),
        this, SLOT(reject())
    );
}

ResultViewer::~ResultViewer()
{}

void ResultViewer::clear()
{
    mUI.webView->setContent(QByteArray());
}

void ResultViewer::loadContent(Evaluator* evaluator)
{
    mReport.clear();
    evaluator->getReport(mReport);
    mUI.webView->setContent(mReport);

    mResults.clear();
    evaluator->getResults(mResults);

    mARF.clear();
    evaluator->getARF(mARF);
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