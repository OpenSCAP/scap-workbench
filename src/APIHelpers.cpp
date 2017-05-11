/*
 * Copyright 2014 Red Hat Inc., Durham, North Carolina.
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

#include "APIHelpers.h"
#include <QObject>
#include <QTextDocument>

extern "C"
{
#include <oscap_error.h>
#include <xccdf_policy.h>
}

QString oscapTextIteratorGetPreferred(struct oscap_text_iterator* it, const QString& lang)
{
    oscap_text* preferred_s = oscap_textlist_get_preferred_text(it, lang.isEmpty() ? NULL : lang.toUtf8().constData());
    oscap_text_iterator_free(it);
    const QString ret = QString::fromUtf8(oscap_text_get_text(preferred_s));
    return ret;
}

QString oscapItemGetReadableTitle(struct xccdf_item* item, struct xccdf_policy* policy, const QString& lang)
{
    struct oscap_text_iterator* title_it = xccdf_item_get_title(item);
    char* unresolved = oscap_textlist_get_preferred_plaintext(title_it, lang.isEmpty() ? NULL : lang.toUtf8().constData());
    oscap_text_iterator_free(title_it);
    if (!unresolved)
        return "";
    char* resolved = xccdf_policy_substitute(Qt::escape(QString::fromUtf8(unresolved)).toUtf8().constData(), policy);
    free(unresolved);
    const QString ret = QString::fromUtf8(resolved);
    free(resolved);
    return ret;
}

QString oscapItemGetReadableDescription(struct xccdf_item *item, struct xccdf_policy *policy, const QString& lang)
{
    struct oscap_text_iterator* desc_it = xccdf_item_get_description(item);
    oscap_text* unresolved = oscap_textlist_get_preferred_text(desc_it, lang.isEmpty() ? NULL : lang.toUtf8().constData());
    oscap_text_iterator_free(desc_it);
    if (!unresolved)
        return "";
    char* resolved = xccdf_policy_substitute(oscap_text_get_text(unresolved), policy);
    const QString ret = QString::fromUtf8(resolved);
    free(resolved);
    return ret;
}

QString oscapErrDesc()
{
    return QString::fromUtf8(oscap_err_desc());
}

QString oscapErrGetFullError()
{
    char* fullErrorCstr = oscap_err_get_full_error();
    QString fullError = QString::fromUtf8(fullErrorCstr);
    free(fullErrorCstr);
    return fullError;
}
