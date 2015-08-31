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

#ifndef SCAP_WORKBENCH_API_HELPERS_H_
#define SCAP_WORKBENCH_API_HELPERS_H_

#include "ForwardDecls.h"

#include <QString>

extern "C"
{
#include <xccdf_benchmark.h>
#include <xccdf_policy.h>
}

/**
 * Goes through the text iterator and returns preferred text depending on language
 *
 * This function frees the iterator itself, it can't be used after this function terminates.
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 */
QString oscapTextIteratorGetPreferred(struct oscap_text_iterator* it, const QString& lang = "");

/**
 * Get human readable title of the given XCCDF Item. The title is selected based on the given
 * preferred language and then the XCCDF Substitution is resolved in accordance with given
 * XCCDF policy.
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 */
QString oscapItemGetReadableTitle(struct xccdf_item* item, struct xccdf_policy* policy, const QString& lang = "");

/**
 * Get human readable description of the given XCCDF Item. The description is selected based
 * on the given preferred language and then the XCCDF Substitution is resolved in accordance
 * with given XCCDF policy.
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 */
QString oscapItemGetReadableDescription(struct xccdf_item* item, struct xccdf_policy* policy, const QString& lang = "");

/**
 * Returns QString containing utf8 contents of oscap_err_desc()
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 */
QString oscapErrDesc();

/**
 * Returns QString containing utf8 contents of oscap_err_get_full_error()
 *
 * @exception nothrow This function is guaranteed to not throw any exceptions.
 */
QString oscapErrGetFullError();

#endif
